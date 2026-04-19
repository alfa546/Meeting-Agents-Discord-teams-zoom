// Claude/ChatGPT/Gemini Style JavaScript
const markedOptions = {
    breaks: true,
    gfm: true,
    highlight: function(code, lang) {
        const language = hljs.getLanguage(lang) ? lang : 'plaintext';
        return hljs.highlight(code, { language }).value;
    }
};
marked.setOptions(markedOptions);

let sessionId = localStorage.getItem('limo_session_id');
if (!sessionId) {
    sessionId = 'sess_' + Math.random().toString(36).slice(2, 10);
    localStorage.setItem('limo_session_id', sessionId);
}

const chatContainer = document.getElementById('chatContainer');
const promptEl = document.getElementById('prompt');
const sendBtn = document.getElementById('sendBtn');
const chatHistoryContainer = document.getElementById('chatHistory');

let selectedModel = localStorage.getItem('limo_selected_model') || 'openrouter/elephant-alpha';

// Auto-resize textarea
promptEl.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 200) + 'px';
});

promptEl.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend(e);
    }
});

function renderMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role === 'user' ? 'user' : 'ai'}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = role === 'user' ? '👤' : '🤖';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    if (role === 'user') {
        contentDiv.textContent = content;
    } else {
        const rawHtml = marked.parse(content);
        contentDiv.innerHTML = DOMPurify.sanitize(rawHtml);
        
        // Highlight code blocks
        contentDiv.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function api(path, payload) {
    const res = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    return await res.json();
}

async function loadHistory() {
    try {
        const data = await api('/api/session/history', { session_id: sessionId });
        chatContainer.innerHTML = '';
        if (data.history && data.history.length > 0) {
            data.history.forEach(m => renderMessage(m.role, m.content));
        } else {
            chatContainer.innerHTML = '<div class="empty-state"><div class="empty-state-title">How can I help you today?</div></div>';
        }
    } catch (e) {
        console.error("LoadHistory Error:", e);
    }
}

async function handleSend(event) {
    const text = promptEl.value.trim();
    if (!text) return;

    promptEl.value = '';
    promptEl.style.height = 'auto';
    
    // Remove empty state
    const empty = chatContainer.querySelector('.empty-state');
    if (empty) empty.remove();

    renderMessage('user', text);

    // AI thinking state
    const thinkingId = 'thinking-' + Date.now();
    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'message ai';
    thinkingDiv.id = thinkingId;
    thinkingDiv.innerHTML = '<div class="message-avatar">🤖</div><div class="message-content">Thinking...</div>';
    chatContainer.appendChild(thinkingDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    try {
        const data = await api('/api/chat', { session_id: sessionId, message: text, model: selectedModel });
        document.getElementById(thinkingId).remove();
        renderMessage('ai', data.answer || 'No response');
        loadRecentChats();
    } catch (err) {
        document.getElementById(thinkingId).innerHTML = '<div class="message-avatar">🤖</div><div class="message-content" style="color: #f85149;">Error connecting to API</div>';
    }
}

async function loadRecentChats() {
    try {
        const res = await fetch('/api/recent-chats', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        chatHistoryContainer.innerHTML = '';
        if (data.chats) {
            data.chats.forEach(chat => {
                const item = document.createElement('div');
                item.className = `chat-item ${chat.session_id === sessionId ? 'active' : ''}`;
                item.textContent = chat.title;
                item.onclick = () => {
                    sessionId = chat.session_id;
                    localStorage.setItem('limo_session_id', sessionId);
                    loadHistory();
                    loadRecentChats();
                };
                chatHistoryContainer.appendChild(item);
            });
        }
    } catch (e) { }
}

function newChat() {
    sessionId = 'sess_' + Math.random().toString(36).slice(2, 10);
    localStorage.setItem('limo_session_id', sessionId);
    loadHistory();
    loadRecentChats();
}

// Initial load
loadHistory();
loadRecentChats();
