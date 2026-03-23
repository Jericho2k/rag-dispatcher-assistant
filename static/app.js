let currentChatId = null;

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const saved = localStorage.getItem('theme') || 'dark';
  document.body.className = saved;
  loadChats();
  loadDocs();
});

// ── Theme ─────────────────────────────────────────────────────────────────────
function toggleTheme() {
  const next = document.body.classList.contains('dark') ? 'light' : 'dark';
  document.body.className = next;
  localStorage.setItem('theme', next);
}

// ── Page navigation ───────────────────────────────────────────────────────────
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
  document.getElementById(`page-${name}`).classList.remove('hidden');
  if (name === 'settings') loadDocs();
}

// ── Chats ─────────────────────────────────────────────────────────────────────
async function loadChats() {
  const res = await fetch('/api/chats');
  const chats = await res.json();
  renderChatList(chats);
}

function renderChatList(chats) {
  const list = document.getElementById('chatList');
  list.innerHTML = '';
  const entries = Object.entries(chats).reverse();
  entries.forEach(([id, data]) => {
    const item = document.createElement('div');
    item.className = 'chat-item' + (id === currentChatId ? ' active' : '');
    item.innerHTML = `
      <span class="chat-item-title">${data.title}</span>
      <button class="chat-item-del" onclick="deleteChat(event,'${id}')">✕</button>
    `;
    item.addEventListener('click', () => openChat(id, data.title));
    list.appendChild(item);
  });
}

async function newChat() {
  showPage('chat');
  const res = await fetch('/api/chats', { method: 'POST' });
  const data = await res.json();
  currentChatId = data.chat_id;
  clearMessages();
  document.getElementById('inputArea').style.display = 'block';
  document.getElementById('chatEmpty').style.display = 'none';
  await loadChats();
  document.getElementById('questionInput').focus();
}

async function openChat(id, title) {
  showPage('chat');
  currentChatId = id;
  document.getElementById('chatEmpty').style.display = 'none';
  document.getElementById('inputArea').style.display = 'block';

  const res = await fetch(`/api/chats/${id}/messages`);
  const messages = await res.json();
  clearMessages();
  messages.forEach(m => renderMessage(m.role, m.content, m.sources || []));
  scrollToBottom();
  await loadChats();
}

async function deleteChat(e, id) {
  e.stopPropagation();
  await fetch(`/api/chats/${id}`, { method: 'DELETE' });
  if (currentChatId === id) {
    currentChatId = null;
    clearMessages();
    document.getElementById('inputArea').style.display = 'none';
    document.getElementById('chatEmpty').style.display = 'flex';
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

  const avatarText = role === 'user' ? 'Вы' : 'AI';
  const roleLabel = role === 'user' ? 'Вы' : 'Ассистент';

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
    <div class="message-avatar">${avatarText}</div>
    <div class="message-body">
      <div class="message-role">${roleLabel}</div>
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

// ── Send question ─────────────────────────────────────────────────────────────
async function sendQuestion() {
  const input = document.getElementById('questionInput');
  const question = input.value.trim();
  if (!question || !currentChatId) return;

  input.value = '';
  autoResize(input);
  document.getElementById('sendBtn').disabled = true;

  renderMessage('user', question);

  // Typing indicator
  const typingDiv = document.createElement('div');
  typingDiv.className = 'message assistant typing';
  typingDiv.innerHTML = `
    <div class="message-avatar">AI</div>
    <div class="message-body">
      <div class="message-role">Ассистент</div>
      <div class="message-text"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
    </div>
  `;
  document.getElementById('messages').appendChild(typingDiv);
  scrollToBottom();

  try {
    const res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: currentChatId, question })
    });
    const data = await res.json();
    typingDiv.remove();

    if (data.error) {
      renderMessage('assistant', data.error);
    } else {
      renderMessage('assistant', data.answer, data.sources);
      await loadChats(); // обновить заголовок чата
    }
  } catch (e) {
    typingDiv.remove();
    renderMessage('assistant', 'Ошибка соединения с сервером.');
  }

  document.getElementById('sendBtn').disabled = false;
  scrollToBottom();
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendQuestion();
  }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

// ── Docs ──────────────────────────────────────────────────────────────────────
async function loadDocs() {
  const res = await fetch('/api/docs');
  const docs = await res.json();
  const list = document.getElementById('docList');
  list.innerHTML = docs.map(d => `
    <div class="doc-item">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
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
    const res = await fetch('/api/docs/upload', { method: 'POST', body: form });
    const data = await res.json();
    status.className = 'upload-status success';
    status.textContent = `✓ Добавлено: ${data.uploaded.join(', ')}`;
    loadDocs();
  } catch (e) {
    status.className = 'upload-status error';
    status.textContent = 'Ошибка загрузки.';
  }
}
