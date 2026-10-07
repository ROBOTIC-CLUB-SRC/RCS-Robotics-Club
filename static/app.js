// ==========================================================================
// RCS Robotics Club — Public Website JavaScript
// ==========================================================================

let DATA = {
  members: [],
  projects: [],
  events: [],
  quizzes: [],
  games: [],
  learning: [],
  goals: { members: 50, projects: 20, events: 20, resources: 30 }
};

// Escape HTML for XSS prevention
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }[c]));
}

// Format date into Month and Day for the red date badge
function parseDateParts(dateStr) {
  if (!dateStr) return { month: 'TBD', day: '--' };
  try {
    const d = new Date(dateStr + 'T00:00:00');
    if (isNaN(d.getTime())) return { month: 'TBD', day: '--' };
    const month = d.toLocaleDateString('en-US', { month: 'short' }).toUpperCase();
    const day = d.toLocaleDateString('en-US', { day: '2-digit' });
    return { month, day };
  } catch (e) {
    return { month: 'TBD', day: '--' };
  }
}

// Fetch live database data
async function loadData() {
  try {
    const res = await fetch('/api/public/all');
    if (!res.ok) throw new Error('Failed to load data');
    DATA = await res.json();
    renderAll();
  } catch (err) {
    console.error('Error fetching club data:', err);
  }
}

// Main Render Function
function renderAll() {
  renderStatRings();
  renderHeroFeatured();
  renderMembers();
  renderProjects();
  renderEvents();
  renderResources();
  renderQuizzes();
}

// 1. Live Stat Rings (conic-gradient, relative to config goals)
function renderStatRings() {
  const goals = DATA.goals || { members: 50, projects: 20, events: 20, resources: 30 };
  const membersCount = DATA.members?.length || 0;
  const projectsCount = DATA.projects?.length || 0;
  const eventsCount = DATA.events?.length || 0;
  const resourcesCount = DATA.learning?.length || 0;

  const pctMembers = Math.min(100, Math.round((membersCount / (goals.members || 50)) * 100));
  const pctProjects = Math.min(100, Math.round((projectsCount / (goals.projects || 20)) * 100));
  const pctEvents = Math.min(100, Math.round((eventsCount / (goals.events || 20)) * 100));
  const pctResources = Math.min(100, Math.round((resourcesCount / (goals.resources || 30)) * 100));

  const countMembersEl = document.getElementById('statCountMembers');
  if (countMembersEl) countMembersEl.textContent = membersCount;
  const ringMembersEl = document.getElementById('donutRingMembers');
  if (ringMembersEl) ringMembersEl.style.setProperty('--percent', pctMembers);

  const countProjectsEl = document.getElementById('statCountProjects');
  if (countProjectsEl) countProjectsEl.textContent = projectsCount;
  const ringProjectsEl = document.getElementById('donutRingProjects');
  if (ringProjectsEl) ringProjectsEl.style.setProperty('--percent', pctProjects);

  const countEventsEl = document.getElementById('statCountEvents');
  if (countEventsEl) countEventsEl.textContent = eventsCount;
  const ringEventsEl = document.getElementById('donutRingEvents');
  if (ringEventsEl) ringEventsEl.style.setProperty('--percent', pctEvents);

  const countResourcesEl = document.getElementById('statCountResources');
  if (countResourcesEl) countResourcesEl.textContent = resourcesCount;
  const ringResourcesEl = document.getElementById('donutRingResources');
  if (ringResourcesEl) ringResourcesEl.style.setProperty('--percent', pctResources);
}

// 2. Hero Featured Column
function renderHeroFeatured() {
  const activeCountEl = document.getElementById('heroActiveProjectsCount');
  if (activeCountEl) {
    activeCountEl.textContent = DATA.projects?.length || 0;
  }

  const firstProj = DATA.projects?.[0];
  if (firstProj) {
    const titleEl = document.getElementById('heroFeaturedProjName');
    if (titleEl) titleEl.textContent = firstProj.title;

    const descEl = document.getElementById('heroFeaturedProjDesc');
    if (descEl) descEl.textContent = firstProj.description || '';

    const techString = firstProj.tech || firstProj.technology || 'ESP32, IR array, PID';
    const chips = techString.split(',').map(s => s.trim()).filter(Boolean);
    const chipsContainer = document.getElementById('heroTechChips');
    if (chipsContainer && chips.length > 0) {
      chipsContainer.innerHTML = chips
        .map(chip => `<span class="pill-chip chip-blue">${esc(chip)}</span>`)
        .join('');
    }
  }

  if (DATA.club?.description) {
    const descEl = document.getElementById('heroDesc');
    if (descEl) descEl.textContent = DATA.club.description;
  }
}

// 3. Members Grid
function renderMembers() {
  const grid = document.getElementById('membersGrid');
  if (!grid) return;

  grid.innerHTML = (DATA.members || []).map(m => {
    const avatarContent = m.image_url
      ? `<img class="member-photo-img" src="${esc(m.image_url)}" alt="${esc(m.name)}" loading="lazy">`
      : `<div class="member-avatar-box" aria-hidden="true">${esc((m.name || 'R')[0])}</div>`;

    const skillsHtml = (m.skills || 'Robotics')
      .split(',')
      .map(s => `<span class="pill-chip chip-blue">${esc(s.trim())}</span>`)
      .join(' ');

    return `
      <article class="card member-card">
        ${avatarContent}
        <div class="member-body">
          <h3 class="member-name">${esc(m.name)}</h3>
          <div class="member-role">${esc(m.role || 'Club Member')}</div>
          <small style="color:var(--text-muted)">${esc(m.department || '')} ${m.year ? '• ' + esc(m.year) : ''}</small>
          <p class="member-bio">${esc(m.bio || '')}</p>
          <div class="pills-flex-wrap" style="margin-top:auto">${skillsHtml}</div>
        </div>
      </article>
    `;
  }).join('');
}

// 4. Projects Grid (3 cards with image, status badge pill, technology chips, View button)
function renderProjects() {
  const grid = document.getElementById('projectsGrid');
  if (!grid) return;

  grid.innerHTML = (DATA.projects || []).slice(0, 3).map(p => {
    const techChips = (p.tech || p.technology || '')
      .split(',')
      .map(t => t.trim())
      .filter(Boolean)
      .map(t => `<span class="pill-chip chip-blue">${esc(t)}</span>`)
      .join(' ');

    const status = p.status || 'Active';
    const isPrototype = status.toLowerCase().includes('proto');
    const badgeClass = isPrototype ? 'chip-red' : 'chip-blue';

    return `
      <article class="card project-card">
        <div class="project-card-top">
          <div class="project-image-box">
            ${p.image_url
              ? `<img src="${esc(p.image_url)}" alt="${esc(p.title)}" loading="lazy">`
              : `<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>`
            }
          </div>
          <div class="project-status-row">
            <span class="pill-chip ${badgeClass}">${esc(status)}</span>
            <small style="color:var(--text-muted);font-size:11px">${esc(p.category || 'Robotics')}</small>
          </div>
          <h3 class="project-title">${esc(p.title)}</h3>
          <p class="project-desc">${esc(p.description || '')}</p>
          <div class="tech-chips-group">${techChips}</div>
        </div>
        <div class="project-card-footer">
          <button class="btn btn-red btn-pill" onclick="viewProjectDetails(${p.id})">View</button>
          ${p.demo_url ? `<a href="${esc(p.demo_url)}" target="_blank" rel="noopener noreferrer" class="view-projects-arrow-link">Demo &rarr;</a>` : ''}
        </div>
      </article>
    `;
  }).join('');
}

// 5. Events List (cards with red date badge)
function renderEvents() {
  const list = document.getElementById('eventsGrid');
  if (!list) return;

  list.innerHTML = (DATA.events || []).map(e => {
    const { month, day } = parseDateParts(e.date);

    return `
      <article class="card event-card">
        <div class="event-date-badge" aria-label="Event date ${month} ${day}">
          <span class="event-date-month">${esc(month)}</span>
          <span class="event-date-day">${esc(day)}</span>
        </div>
        <div class="event-info">
          <h3 class="event-title">${esc(e.title)}</h3>
          <div class="event-meta">${esc(e.time || '')} ${e.venue ? '• ' + esc(e.venue) : ''}</div>
          <p class="event-desc">${esc(e.description || '')}</p>
        </div>
        <div>
          ${e.registration_url
            ? `<a class="btn btn-red btn-pill" href="${esc(e.registration_url)}" target="_blank" rel="noopener noreferrer">Register &rarr;</a>`
            : `<button class="btn btn-ghost" onclick="alert('Registration opening soon!')">Coming Soon</button>`
          }
        </div>
      </article>
    `;
  }).join('');
}

// 6. Resources Grid (cards with blue category pill and red "Open Resource" pill button)
function renderResources() {
  const grid = document.getElementById('learningGrid');
  if (!grid) return;

  grid.innerHTML = (DATA.learning || []).map(l => `
    <article class="card resource-card">
      <div>
        <div class="resource-head">
          <span class="pill-chip chip-blue">${esc(l.level || 'Tutorial')} • ${esc(l.category || 'Track')}</span>
          <span class="resource-order-badge">#${String(l.order_no || 0).padStart(2, '0')}</span>
        </div>
        <h3 class="resource-title">${esc(l.title.replace(/^\\d+\\s•\\s/, ''))}</h3>
        <p class="resource-summary">${esc(l.description)}</p>
      </div>
      <div class="resource-action-row">
        <button class="btn btn-red btn-pill" onclick="openLesson(${l.id})">Open Resource</button>
      </div>
    </article>
  `).join('');
}

// 7. Quizzes List
function renderQuizzes() {
  const list = document.getElementById('quizList');
  if (!list) return;

  list.innerHTML = (DATA.quizzes || []).map(q => `
    <div class="quiz-item-card">
      <div>
        <h4 style="font-size:16px;margin-bottom:4px">${esc(q.title)}</h4>
        <small style="color:var(--text-muted)">${esc(q.topic)} • ${esc(q.difficulty)}</small>
      </div>
      <button class="btn btn-red btn-pill" onclick="startQuiz(${q.id})">Start Quiz</button>
    </div>
  `).join('');
}

// Modal open/close for resources
function openLesson(id) {
  const lesson = (DATA.learning || []).find(x => x.id === id);
  if (!lesson) return;

  const modal = document.getElementById('resourceModal');
  const catEl = document.getElementById('modalCategory');
  const titleEl = document.getElementById('modalTitle');
  const bodyEl = document.getElementById('modalContent');

  if (catEl) catEl.textContent = `${lesson.level} • ${lesson.category}`;
  if (titleEl) titleEl.textContent = lesson.title;
  if (bodyEl) {
    bodyEl.innerHTML = `
      <p style="margin-bottom:14px;color:var(--text);font-weight:500">${esc(lesson.description)}</p>
      <div style="white-space:pre-wrap;background:var(--surface-2);padding:18px;border-radius:12px;border:1px solid var(--border-subtle)">${esc(lesson.content)}</div>
    `;
  }

  if (modal && typeof modal.showModal === 'function') {
    modal.showModal();
  } else {
    alert(`${lesson.title}\n\n${lesson.content}`);
  }
}

function closeLessonModal() {
  const modal = document.getElementById('resourceModal');
  if (modal && typeof modal.close === 'function') {
    modal.close();
  }
}

// Project Details Dialog
function viewProjectDetails(id) {
  const proj = (DATA.projects || []).find(x => x.id === id);
  if (!proj) return;

  const modal = document.getElementById('resourceModal');
  const catEl = document.getElementById('modalCategory');
  const titleEl = document.getElementById('modalTitle');
  const bodyEl = document.getElementById('modalContent');

  if (catEl) catEl.textContent = `${proj.status || 'Active'} • ${proj.category || 'Engineering'}`;
  if (titleEl) titleEl.textContent = proj.title;
  if (bodyEl) {
    bodyEl.innerHTML = `
      <p style="margin-bottom:16px;font-size:15px;color:var(--text)">${esc(proj.description || '')}</p>
      <div style="margin-bottom:14px">
        <strong>Tech Stack:</strong>
        <div class="tech-chips-group" style="margin-top:6px">
          ${(proj.tech || '').split(',').map(t => `<span class="pill-chip chip-blue">${esc(t.trim())}</span>`).join(' ')}
        </div>
      </div>
      ${proj.demo_url ? `<p><a href="${esc(proj.demo_url)}" target="_blank" class="btn btn-blue btn-pill" style="margin-top:10px">Open Project Demo &rarr;</a></p>` : ''}
    `;
  }

  if (modal && typeof modal.showModal === 'function') {
    modal.showModal();
  }
}

// Interactive Quiz Execution
function startQuiz(id) {
  const q = (DATA.quizzes || []).find(x => x.id === id);
  if (!q) return;

  let questions = [];
  try {
    questions = JSON.parse(q.questions_json);
  } catch (e) {
    questions = [];
  }
  if (!questions.length) return;

  let score = 0;
  let idx = 0;
  const wrap = document.getElementById('quizArea');

  function renderQuestion() {
    if (idx >= questions.length) {
      wrap.innerHTML = `
        <div class="quiz-info-col">
          <span class="pill-chip chip-red">RESULT</span>
          <h3 class="quiz-title">Score: ${score} / ${questions.length} 🎉</h3>
          <p>${score === questions.length ? 'Outstanding! Robot brain = ONLINE ⚡' : 'Solid attempt. Review the academy tracks and try again!'}</p>
          <button class="btn btn-red btn-pill" onclick="location.reload()" style="margin-top:14px">Back to Quizzes</button>
        </div>
      `;
      return;
    }

    const item = questions[idx];
    wrap.innerHTML = `
      <div class="quiz-info-col">
        <span class="pill-chip chip-blue">QUESTION ${idx + 1} OF ${questions.length}</span>
        <h3 class="quiz-title">${esc(q.title)}</h3>
        <p>Current score: ${score}</p>
      </div>
      <div class="quiz-list-col">
        <div style="background:var(--surface-2);padding:24px;border-radius:18px;border:1px solid var(--border-subtle)">
          <h4 style="font-size:18px;margin-bottom:16px">${esc(item.q)}</h4>
          <div style="display:grid;gap:10px">
            ${item.options.map((opt, optIdx) => `
              <button class="btn btn-ghost" style="text-align:left;width:100%;justify-content:flex-start" onclick="handleQuizAnswer(${optIdx})">
                ${esc(opt)}
              </button>
            `).join('')}
          </div>
          <div id="quizFeedbackMsg" style="margin-top:14px;font-size:14px;min-height:22px"></div>
        </div>
      </div>
    `;

    window.handleQuizAnswer = function(selectedIdx) {
      const fbMsg = document.getElementById('quizFeedbackMsg');
      const isCorrect = (selectedIdx === item.answer);
      if (isCorrect) score++;

      if (fbMsg) {
        fbMsg.style.color = isCorrect ? 'var(--blue-bright)' : 'var(--red-bright)';
        fbMsg.textContent = (isCorrect ? '✓ Correct! ' : '✗ Incorrect. ') + (item.explain || '');
      }

      setTimeout(() => {
        idx++;
        renderQuestion();
      }, 1400);
    };
  }

  renderQuestion();
}

// Mini Games
function startSensorGame() {
  const el = document.getElementById('sensorGame');
  if (!el) return;
  el.classList.remove('hidden');
  el.innerHTML = `
    <h4 style="margin-bottom:8px">Distance Sensor Calibration</h4>
    <p style="font-size:13px;color:var(--text-muted);margin-bottom:12px">Calibrate the sensor into the target window (45cm &ndash; 55cm).</p>
    <label for="sensRange" class="visually-hidden">Distance Sensor Slider</label>
    <input id="sensRange" type="range" min="0" max="100" value="20" class="pill-input" style="width:100%;padding:4px" oninput="document.getElementById('sensVal').textContent=this.value">
    <div style="margin:10px 0;font-size:14px">Current reading: <strong id="sensVal" style="color:var(--blue-bright)">20</strong> cm</div>
    <button class="btn btn-red btn-pill" onclick="checkSensorCalibration()">Calibrate</button>
    <span id="sensResult" style="margin-left:12px;font-size:13px"></span>
  `;
}

function checkSensorCalibration() {
  const val = Number(document.getElementById('sensRange')?.value || 0);
  const res = document.getElementById('sensResult');
  if (val >= 45 && val <= 55) {
    if (res) {
      res.style.color = 'var(--blue-bright)';
      res.textContent = '✓ Locked! Sensor status = ONLINE ⚡';
    }
  } else {
    if (res) {
      res.style.color = 'var(--red-bright)';
      res.textContent = '✗ Out of bounds. Tune closer to 50cm.';
    }
  }
}

function startPIDGame() {
  const el = document.getElementById('pidGame');
  if (!el) return;
  el.classList.remove('hidden');
  el.innerHTML = `
    <h4 style="margin-bottom:8px">PID Proportional Control</h4>
    <p style="font-size:13px;color:var(--text-muted);margin-bottom:12px">Adjust Kp to 0.60 to cancel steering error smoothly.</p>
    <label for="kpRange" class="visually-hidden">Kp Slider</label>
    <input id="kpRange" type="range" min="0" max="100" value="25" class="pill-input" style="width:100%;padding:4px" oninput="document.getElementById('kpVal').textContent=(this.value/100).toFixed(2)">
    <div style="margin:10px 0;font-size:14px">Proportional Gain (Kp): <strong id="kpVal" style="color:var(--blue-bright)">0.25</strong></div>
    <button class="btn btn-red btn-pill" onclick="checkPIDGain()">Engage Loop</button>
    <span id="pidResult" style="margin-left:12px;font-size:13px"></span>
  `;
}

function checkPIDGain() {
  const val = Number(document.getElementById('kpRange')?.value || 0);
  const res = document.getElementById('pidResult');
  if (val === 60) {
    if (res) {
      res.style.color = 'var(--blue-bright)';
      res.textContent = '✓ Optimal damping! Line tracking steady 🎯';
    }
  } else {
    if (res) {
      res.style.color = 'var(--red-bright)';
      res.textContent = val < 60 ? '✗ Sluggish response (under-damped).' : '✗ Oscillation detected (over-damped).';
    }
  }
}

let pathMoves = '';
function startPathGame() {
  const el = document.getElementById('pathGame');
  if (!el) return;
  pathMoves = '';
  el.classList.remove('hidden');
  el.innerHTML = `
    <h4 style="margin-bottom:8px">Warehouse Grid Route</h4>
    <p style="font-size:13px;color:var(--text-muted);margin-bottom:12px">Click the sequence to guide bot to destination (Right, Right, Down, Down, Right).</p>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      ${['R', 'R', 'D', 'D', 'R'].map(m => `<button class="btn btn-ghost" onclick="stepPathMove(this, '${m}')">${m}</button>`).join('')}
    </div>
    <div id="pathTracker" style="margin-top:12px;font-size:14px;color:var(--blue-bright)"></div>
  `;
}

function stepPathMove(btn, move) {
  btn.disabled = true;
  pathMoves += move;
  const tracker = document.getElementById('pathTracker');
  if (tracker) {
    tracker.textContent = `Path sequence: ${pathMoves}`;
    if (pathMoves === 'RRDDR') {
      tracker.innerHTML = `Path sequence: ${pathMoves} &mdash; <strong style="color:var(--blue-bright)">Route Completed! Collision-free 🗺️</strong>`;
    }
  }
}

// Navigation mobile toggle
function toggleNav() {
  const menu = document.getElementById('navMenu');
  if (menu) menu.classList.toggle('open');
}

// Check URL query parameters on load to prefill feedback form
function handlePrefillFeedback() {
  const params = new URLSearchParams(window.location.search);
  const prefillMsg = params.get('message');
  if (prefillMsg) {
    const textarea = document.getElementById('fbMessage');
    if (textarea) {
      textarea.value = prefillMsg;
      const feedbackSection = document.getElementById('feedback');
      if (feedbackSection) {
        feedbackSection.scrollIntoView({ behavior: 'smooth' });
        setTimeout(() => textarea.focus(), 300);
      }
    }
  }
}

// Feedback Form Submission Handler
document.getElementById('ideaForm')?.addEventListener('submit', async e => {
  e.preventDefault();
  const form = e.target;
  const msgEl = document.getElementById('ideaMsg');
  const payload = Object.fromEntries(new FormData(form));

  try {
    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await res.json();

    if (res.ok) {
      if (msgEl) {
        msgEl.style.color = 'var(--blue-bright)';
        msgEl.textContent = 'Idea submitted successfully! Team can review in the control room.';
      }
      form.reset();
    } else {
      if (msgEl) {
        msgEl.style.color = 'var(--red-bright)';
        msgEl.textContent = result.error || 'Submission failed. Please try again.';
      }
    }
  } catch (err) {
    if (msgEl) {
      msgEl.style.color = 'var(--red-bright)';
      msgEl.textContent = 'Network error. Please try again.';
    }
  }
});

// Initialization
document.addEventListener('DOMContentLoaded', () => {
  loadData();
  handlePrefillFeedback();
});

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/sw.js').catch(() => {});
}
