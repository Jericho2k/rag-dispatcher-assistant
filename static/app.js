let currentChatId = null;
let currentUser = null;

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const saved = localStorage.getItem('theme') || 'dark';
  document.body.className = saved;
  const token = localStorage.getItem('token');
  if (token) initApp();
});

// ── Theme ─────────────────────────────────────────────────────────────────────
function toggleTheme() {
  const next = document.body.classList.contains('dark') ? 'light' : 'dark';
  document.body.className = next;
  localStorage.setItem('theme', next);
}

// ── Password toggle ───────────────────────────────────────────────────────────
function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  const isPassword = input.type === 'password';
  input.type = isPassword ? 'text' : 'password';
  btn.querySelector('.eye-icon').style.opacity = isPassword ? '0.4' : '1';
}

// ── Auth ──────────────────────────────────────────────────────────────────────
async function submitAuth() {
  const email = document.getElementById('authEmail').value.trim();
  const password = document.getElementById('authPassword').value;
  const errorEl = document.getElementById('authError');
  errorEl.textContent = '';

  if (!email || !password) { errorEl.textContent = 'Заполните все поля'; return; }

  const form = new FormData();
  form.append('username', email);
  form.append('password', password);

  try {
    const res = await fetch('/api/auth/login', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) { errorEl.textContent = data.detail || 'Ошибка'; return; }
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('role', data.role);
    localStorage.setItem('name', data.name || '');
    initApp();
  } catch { errorEl.textContent = 'Ошибка соединения'; }
}

function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('role');
  localStorage.removeItem('name');
  currentUser = null;
  currentChatId = null;
  document.getElementById('authScreen').classList.remove('hidden');
  document.getElementById('appLayout').classList.add('hidden');
}

async function initApp() {
  const token = localStorage.getItem('token');
  try {
    const res = await fetch('/api/auth/me', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) { logout(); return; }
    currentUser = await res.json();
  } catch { logout(); return; }

  document.getElementById('authScreen').classList.add('hidden');
  document.getElementById('appLayout').classList.remove('hidden');

  showHome();
  loadChats();
}

// ── Home ──────────────────────────────────────────────────────────────────────
function showHome() {
  showPage('home');
  currentChatId = null;
  const name = currentUser?.name || localStorage.getItem('name') || '';
  const welcomeEl = document.getElementById('welcomeText');
  if (name && welcomeEl) {
    welcomeEl.textContent = `Добро пожаловать, ${name}! Задавайте вопросы по нормативным документам.`;
  }
  loadChats();
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function authHeaders() {
  return { 'Authorization': `Bearer ${localStorage.getItem('token')}` };
}

// ── Page navigation ───────────────────────────────────────────────────────────
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
  document.getElementById(`page-${name}`).classList.remove('hidden');
  if (name === 'settings') {
    updateAccountInfo();
    loadPersonalDocs();
    if (currentUser?.role === 'admin') {
      loadDocs();
      loadUsers();
    }
  }
}

// ── Chats ─────────────────────────────────────────────────────────────────────
async function loadChats() {
  const res = await fetch('/api/chats', { headers: authHeaders() });
  if (!res.ok) { logout(); return; }
  const chats = await res.json();
  renderChatList(chats);
}

function renderChatList(chats) {
  const list = document.getElementById('chatList');
  list.innerHTML = '';
  chats.forEach(chat => {
    const item = document.createElement('div');
    item.className = 'chat-item' + (chat.id === currentChatId ? ' active' : '');
    item.innerHTML = `
      <span class="chat-item-title">${chat.title}</span>
      <button class="chat-item-del" onclick="deleteChat(event,'${chat.id}')">✕</button>
    `;
    item.addEventListener('click', () => openChat(chat.id));
    list.appendChild(item);
  });
}

async function newChat() {
  showPage('chat');
  const res = await fetch('/api/chats', { method: 'POST', headers: authHeaders() });
  const chat = await res.json();
  currentChatId = chat.id;
  clearMessages();
  await loadChats();
  document.getElementById('questionInput').focus();
}

async function openChat(id) {
  showPage('chat');
  currentChatId = id;
  const res = await fetch(`/api/chats/${id}/messages`, { headers: authHeaders() });
  const messages = await res.json();
  clearMessages();
  messages.forEach(m => renderMessage(m.role, m.content, m.sources || []));
  scrollToBottom();
  await loadChats();
}

async function deleteChat(e, id) {
  e.stopPropagation();
  await fetch(`/api/chats/${id}`, { method: 'DELETE', headers: authHeaders() });
  if (currentChatId === id) {
    currentChatId = null;
    showHome();
  }
  await loadChats();
}

// ── Messages ──────────────────────────────────────────────────────────────────
function clearMessages() {
  document.getElementById('messages').innerHTML = '';
}

function renderMessage(role, content, sources = []) {
  const container = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = `message ${role}`;

  let sourcesHtml = '';
  if (sources.length > 0) {
    const items = sources.map(s => `
      <div class="source-item">
        <div class="source-name">${s.source} · стр. ${s.page}</div>
        <div class="source-text">${s.text}...</div>
      </div>
    `).join('');
    sourcesHtml = `
      <div class="sources">
        <button class="sources-toggle" onclick="toggleSources(this)">
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M3 1l4 4-4 4"/>
          </svg>
          Источники (${sources.length})
        </button>
        <div class="sources-list">${items}</div>
      </div>
    `;
  }

  div.innerHTML = `
    <div class="message-avatar">${role === 'user' ? 'Вы' : 'AI'}</div>
    <div class="message-body">
      <div class="message-role">${role === 'user' ? 'Вы' : 'Ассистент'}</div>
      <div class="message-text">${formatText(content)}</div>
      ${sourcesHtml}
    </div>
  `;
  container.appendChild(div);
  return div;
}

function formatText(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^(\d+)\. /gm, '<br>$1. ')
    .replace(/^- /gm, '<br>• ')
    .replace(/\n/g, '<br>');
}

function toggleSources(btn) {
  btn.classList.toggle('open');
  btn.nextElementSibling.classList.toggle('open');
}

function scrollToBottom() {
  const m = document.getElementById('messages');
  m.scrollTop = m.scrollHeight;
}

// ── Send ──────────────────────────────────────────────────────────────────────
async function sendQuestion() {
  const input = document.getElementById('questionInput');
  const question = input.value.trim();
  if (!question || !currentChatId) return;

  input.value = '';
  autoResize(input);
  document.getElementById('sendBtn').disabled = true;

  renderMessage('user', question);

  const typingDiv = document.createElement('div');
  typingDiv.className = 'message assistant typing';
  typingDiv.innerHTML = `
    <div class="message-avatar">AI</div>
    <div class="message-body">
      <div class="message-role">Ассистент</div>
      <div class="message-text">
        <div class="dot"></div><div class="dot"></div><div class="dot"></div>
      </div>
    </div>
  `;
  document.getElementById('messages').appendChild(typingDiv);
  scrollToBottom();

  try {
    const res = await fetch('/api/ask', {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: currentChatId, question })
    });
    const data = await res.json();
    typingDiv.remove();
    renderMessage('assistant', data.answer || data.error, data.sources || []);
    await loadChats();
  } catch {
    typingDiv.remove();
    renderMessage('assistant', 'Ошибка соединения.');
  }

  document.getElementById('sendBtn').disabled = false;
  scrollToBottom();
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuestion(); }
}

function autoResize(el) {
  el.style.height = '20px';
  if (el.scrollHeight > 20) {
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
    el.style.overflowY = el.scrollHeight > 160 ? 'auto' : 'hidden';
  }
}

// ── Settings ──────────────────────────────────────────────────────────────────
function updateAccountInfo() {
  const el = document.getElementById('accountInfo');
  if (!el || !currentUser) return;
  const name = currentUser.name || localStorage.getItem('name') || '';
  el.innerHTML = `
    ${name ? `Имя: <span>${name}</span><br>` : ''}
    Роль: <span>${currentUser.role === 'admin' ? 'Администратор' : 'Пользователь'}</span>
  `;
}

// ── Shared docs (admin) ───────────────────────────────────────────────────────
async function loadDocs() {
  if (currentUser?.role !== 'admin') return;
  document.getElementById('docsSection').style.display = 'block';

  const res = await fetch('/api/docs', { headers: authHeaders() });
  const docs = await res.json();
  const list = document.getElementById('docList');
  list.innerHTML = docs.map(d => `
    <div class="doc-item">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
      ${d}
    </div>
  `).join('') || '<div style="font-size:0.78rem;color:var(--text3)">Документов нет</div>';
}

async function uploadFiles(files) {
  if (!files.length) return;
  const status = document.getElementById('uploadStatus');
  status.className = 'upload-status';
  status.textContent = `Загружаю ${files.length} файл(ов)...`;

  const form = new FormData();
  Array.from(files).forEach(f => form.append('files', f));

  try {
    const res = await fetch('/api/docs/upload/shared', {
      method: 'POST', headers: authHeaders(), body: form
    });
    const data = await res.json();
    status.className = 'upload-status success';
    status.textContent = `✓ Добавлено: ${data.uploaded.join(', ')}`;
    loadDocs();
  } catch {
    status.className = 'upload-status error';
    status.textContent = 'Ошибка загрузки.';
  }
}

// ── Personal docs ─────────────────────────────────────────────────────────────
async function loadPersonalDocs() {
  const res = await fetch('/api/docs/personal', { headers: authHeaders() });
  const docs = await res.json();
  const list = document.getElementById('personalDocList');
  list.innerHTML = docs.map(d => `
    <div class="doc-item">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
      ${d}
    </div>
  `).join('') || '<div style="font-size:0.78rem;color:var(--text3)">Нет личных документов</div>';
}

async function uploadPersonalFiles(files) {
  if (!files.length) return;
  const status = document.getElementById('personalUploadStatus');
  status.className = 'upload-status';
  status.textContent = `Загружаю ${files.length} файл(ов)...`;

  const form = new FormData();
  Array.from(files).forEach(f => form.append('files', f));

  try {
    const res = await fetch('/api/docs/upload/personal', {
      method: 'POST', headers: authHeaders(), body: form
    });
    const data = await res.json();
    status.className = 'upload-status success';
    status.textContent = `✓ Добавлено: ${data.uploaded.join(', ')}`;
    loadPersonalDocs();
  } catch {
    status.className = 'upload-status error';
    status.textContent = 'Ошибка загрузки.';
  }
}

// ── Users (admin) ─────────────────────────────────────────────────────────────
async function loadUsers() {
  document.getElementById('usersSection').style.display = 'block';
  const res = await fetch('/api/users', { headers: authHeaders() });
  const users = await res.json();
  const list = document.getElementById('userList');
  list.innerHTML = users.map(u => `
    <div class="user-item">
      <div>
        <div style="font-size:0.82rem;color:var(--text)">${u.name || '—'}</div>
        <div style="font-size:0.72rem;color:var(--text2);margin-top:2px">${u.email || ''}</div>
      </div>
      <div style="display:flex;align-items:center;gap:0.5rem">
        <span class="user-item-role">${u.role === 'admin' ? 'Администратор' : 'Пользователь'}</span>
        ${u.role !== 'admin' ? `
          <button onclick="deleteUser('${u.user_id}')" style="
            background:none;border:1px solid var(--border);border-radius:5px;
            color:var(--text3);cursor:pointer;padding:2px 6px;font-size:0.7rem;
            transition:0.15s ease;
          " onmouseover="this.style.borderColor='var(--danger)';this.style.color='var(--danger)'"
             onmouseout="this.style.borderColor='var(--border)';this.style.color='var(--text3)'">
            удалить
          </button>
        ` : ''}
      </div>
    </div>
  `).join('');
}

async function createUser() {
  const name = document.getElementById('newUserName').value.trim();
  const email = document.getElementById('newUserEmail').value.trim();
  const password = document.getElementById('newUserPassword').value;
  const status = document.getElementById('createUserStatus');

  if (!name || !email || !password) {
    status.className = 'upload-status error';
    status.textContent = 'Заполните все поля';
    return;
  }

  status.className = 'upload-status';
  status.textContent = 'Создаю пользователя...';

  try {
    const res = await fetch('/api/users', {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password })
    });
    const data = await res.json();
    if (!res.ok) {
      status.className = 'upload-status error';
      status.textContent = data.detail || 'Ошибка';
      return;
    }
    status.className = 'upload-status success';
    status.textContent = `✓ Пользователь ${email} создан`;
    document.getElementById('newUserName').value = '';
    document.getElementById('newUserEmail').value = '';
    document.getElementById('newUserPassword').value = '';
    loadUsers();
  } catch {
    status.className = 'upload-status error';
    status.textContent = 'Ошибка соединения';
  }
}

async function deleteUser(userId) {
  if (!confirm('Удалить пользователя?')) return;
  await fetch(`/api/users/${userId}`, { method: 'DELETE', headers: authHeaders() });
  loadUsers();
}