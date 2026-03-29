import React, { useState, useRef, useEffect, useCallback } from 'react';
import './App.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const QUICK_ACTIONS = [
  { label: '🤒 Check Symptoms', text: 'I have fever and headache' },
  { label: '🌀 Dizziness / Vertigo', text: 'I am feeling dizzy and lightheaded' },
  { label: '🩺 First Aid — Burns', text: 'First aid for burns' },
  { label: '🩺 First Aid — Cuts', text: 'First aid for cuts and bleeding' },
  { label: '💊 Medicine Info', text: 'What is Dolo 650 used for?' },
  { label: '🔄 Find Substitute', text: "I don't have Crocin, what can I use?" },
  { label: '🏥 Find Hospital', text: 'Find hospitals near 600024' },
  { label: '📋 Upload Prescription', text: '__OCR__' },
];

const INTENT_META = {
  symptoms:     { color: '#10b981', bg: 'rgba(16,185,129,0.12)', label: '🤒 Symptom Check' },
  first_aid:    { color: '#f43f5e', bg: 'rgba(244,63,94,0.12)',  label: '🚨 First Aid' },
  medicine_info:{ color: '#0ea5e9', bg: 'rgba(14,165,233,0.12)', label: '💊 Medicine Info' },
  substitute:   { color: '#8b5cf6', bg: 'rgba(139,92,246,0.12)', label: '🔄 Substitute Finder' },
  hospital:     { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', label: '🏥 Hospital Finder' },
  greeting:     { color: '#0ea5e9', bg: 'rgba(14,165,233,0.12)', label: '⚕️ HealthBot' },
  ocr:          { color: '#06b6d4', bg: 'rgba(6,182,212,0.12)',  label: '📋 Prescription OCR' },
  unknown:      { color: '#64748b', bg: 'rgba(100,116,139,0.1)', label: '💬 Assistant' },
};

const WELCOME_MSG = {
  id: 1, role: 'bot', intent: 'greeting',
  content: `## Welcome to HealthBot India ⚕️

Your AI-powered health assistant — available 24/7.

---

**What I can help you with:**

💊 **Medicine Info** — "What is Augmentin used for?"

🔄 **Medicine Substitutes** — "I don't have Crocin, what else?"

🤒 **Symptom Checker** — "I have fever, dizziness and body ache"

🩺 **First Aid** — "First aid for burns / cuts / heart attack"

🏥 **Find Hospitals** — "Hospitals near 600024"

📋 **Prescription OCR** — Upload a photo of your prescription

---

Type a message or pick a quick action from the sidebar.`,
  time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
};

// Simple markdown-to-HTML renderer (no external library needed)
function renderMarkdown(text) {
  if (!text) return '';
  let html = text
    // Escape HTML first
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Headers
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Links — open in new tab
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    // Blockquote
    .replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>')
    // HR
    .replace(/^---$/gm, '<hr/>')
    // Unordered list items
    .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
    // Ordered list items
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    // Table rows (basic)
    .replace(/^\|(.+)\|$/gm, (match, content) => {
      const cells = content.split('|').map(c => c.trim());
      const isSep = cells.every(c => /^[-:]+$/.test(c));
      if (isSep) return '';
      const tag = 'td';
      return '<tr>' + cells.map(c => `<${tag}>${c}</${tag}>`).join('') + '</tr>';
    })
    // Wrap consecutive <li> in <ul>
    .replace(/(<li>.*<\/li>\n?)+/gs, match => `<ul>${match}</ul>`)
    // Wrap consecutive <tr> in <table>
    .replace(/(<tr>.*<\/tr>\n?)+/gs, match => `<table>${match}</table>`)
    // Paragraphs — blank lines become paragraph breaks
    .replace(/\n\n+/g, '</p><p>')
    // Single newlines become <br>
    .replace(/\n/g, '<br/>');

  return `<p>${html}</p>`;
}

function BotBubble({ content }) {
  return (
    <div
      className="bubble bot-bubble"
      dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
    />
  );
}

function TypingDots() {
  return (
    <div className="message bot-message">
      <div className="bot-avatar">⚕️</div>
      <div className="bubble bot-bubble typing-bubble"><span/><span/><span/></div>
    </div>
  );
}

function IntentTag({ intent }) {
  const meta = INTENT_META[intent] || INTENT_META.unknown;
  if (!intent || intent === 'greeting') return null;
  return (
    <div className="intent-tag" style={{ color: meta.color, borderColor: meta.color + '44', background: meta.bg }}>
      {meta.label}
    </div>
  );
}

function Message({ msg }) {
  const isBot = msg.role === 'bot';
  return (
    <div className={`message ${isBot ? 'bot-message' : 'user-message'}`}>
      {isBot && <div className="bot-avatar">⚕️</div>}
      <div className="bubble-wrap">
        {isBot && <IntentTag intent={msg.intent} />}
        {isBot
          ? <BotBubble content={msg.content} />
          : <div className="bubble user-bubble">{msg.content}</div>
        }
        <div className="msg-time">{msg.time}</div>
      </div>
      {!isBot && <div className="user-avatar">YOU</div>}
    </div>
  );
}

function FileUploadBtn({ onUpload, disabled }) {
  const ref = useRef();
  return (
    <>
      <input type="file" accept="image/*" ref={ref} style={{ display: 'none' }}
        onChange={e => { const f = e.target.files[0]; if (f) { ref.current.value = ''; onUpload(f); } }} />
      <button className="icon-btn upload-btn" title="Upload Prescription" onClick={() => ref.current.click()} disabled={disabled}>📎</button>
    </>
  );
}

let _msgId = 2;

export default function App() {
  const [messages, setMessages] = useState([WELCOME_MSG]);
  const [input, setInput]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth > 900);
  const bottomRef = useRef();
  const inputRef  = useRef();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const addMsg = (role, content, intent = 'unknown') => {
    const m = {
      id: _msgId++, role, content, intent,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages(prev => [...prev, m]);
    return m;
  };

  const sendMessage = useCallback(async (text) => {
    const t = text.trim();
    if (!t || loading) return;
    addMsg('user', t);
    setInput('');
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: t }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      addMsg('bot', data.response, data.intent);
    } catch (err) {
      addMsg('bot',
        `**Cannot reach HealthBot server.**\n\nMake sure backend is running:\n\`cd backend && uvicorn main:app --reload --port 8000\``,
        'unknown'
      );
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 80);
    }
  }, [loading]);

  const handleQuickAction = useCallback((action) => {
    if (action.text === '__OCR__') {
      addMsg('bot', '📎 Click the **attachment button** (📎) next to the message box to upload a prescription image.', 'ocr');
      return;
    }
    sendMessage(action.text);
  }, [sendMessage]);

  const handleUpload = useCallback(async (file) => {
    addMsg('user', `📎 Uploading: **${file.name}** (${(file.size/1024).toFixed(0)}KB)`);
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`${API_BASE}/api/ocr/upload`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      addMsg('bot', data.message, 'ocr');
    } catch (err) {
      addMsg('bot', `**OCR Error.** Install EasyOCR:\n\`pip install easyocr opencv-python-headless\``, 'ocr');
    } finally {
      setLoading(false);
    }
  }, []);

  const clearChat = () => {
    _msgId = 2;
    setMessages([{
      ...WELCOME_MSG, id: 1,
      content: 'Chat cleared. How can I help you?',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); }
  };

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <div className="logo">
            <div className="logo-icon-wrap">⚕️</div>
            <div className="logo-text">
              <div className="logo-title">HealthBot</div>
              <div className="logo-sub">India · AI Assistant</div>
            </div>
          </div>
        </div>

        <div className="sidebar-section-label">Quick Actions</div>
        <nav className="quick-actions">
          {QUICK_ACTIONS.map((a, i) => (
            <button key={i} className="quick-action-btn" onClick={() => handleQuickAction(a)} disabled={loading}>
              {a.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-section-label" style={{ marginTop: 20 }}>Tips</div>
        <div className="tips-box">
          <p>🔎 Be specific: "High fever for 2 days with dizziness"</p>
          <p>💊 Substitutes: "I don't have Augmentin 625"</p>
          <p>🏥 Hospitals: Just type a 6-digit pincode</p>
          <p>📋 OCR: Works on printed &amp; handwritten Rx</p>
        </div>

        <div className="sidebar-footer">
          <div className="disclaimer-badge">
            ⚠️ Informational only. Always consult a qualified doctor.
          </div>
        </div>
      </aside>

      <main className="chat-main">
        <header className="chat-header">
          <button className="sidebar-toggle" onClick={() => setSidebarOpen(o => !o)}>
            {sidebarOpen ? '◀' : '▶'}
          </button>
          <div className="header-info">
            <span className="header-title">HealthBot India</span>
            <div className="status-pill">
              <div className="status-dot" />
              <span className="status-text">ONLINE</span>
            </div>
          </div>
          <div className="header-actions">
            <button className="icon-btn" onClick={clearChat} disabled={loading} title="Clear Chat">🗑️</button>
          </div>
        </header>

        <div className="messages-area">
          {messages.map(m => <Message key={m.id} msg={m} />)}
          {loading && <TypingDots />}
          <div ref={bottomRef} />
        </div>

        <div className="input-bar">
          <FileUploadBtn onUpload={handleUpload} disabled={loading} />
          <textarea
            ref={inputRef}
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Describe symptoms, ask about a medicine, or type a pincode..."
            rows={1}
            disabled={loading}
          />
          <button className="send-btn" onClick={() => sendMessage(input)} disabled={!input.trim() || loading}>
            {loading ? <span className="send-spinner" /> : '➤'}
          </button>
        </div>
        <div className="input-hint">
          <span>Enter</span> to send · <span>Shift+Enter</span> for new line · <span>📎</span> to upload prescription
        </div>
      </main>
    </div>
  );
}